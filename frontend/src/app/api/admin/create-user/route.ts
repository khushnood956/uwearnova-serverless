import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, firstName, lastName, phone, role, requesterEmail } = body;

    if (!email || !password) {
      return NextResponse.json({ error: "Email and password are required." }, { status: 400 });
    }

    const supabaseAdmin = createAdminClient();

    // Verify creator authority: Only admin1 (super_admin) can create super_admin accounts
    if (role === "super_admin") {
      const isSuperAdminRequester = requesterEmail === "admin1@uwearnova.com";
      if (!isSuperAdminRequester) {
        return NextResponse.json(
          { error: "Access Denied: Only the Lead Super Administrator (admin1) can create another Super Administrator." },
          { status: 403 }
        );
      }
    }

    // Determine user_type (admin or staff)
    const isAdminRole = role === "super_admin" || role === "store_admin";
    const userType = isAdminRole ? "admin" : "staff";

    // 1. Create Supabase Auth user
    const { data: authData, error: authError } = await supabaseAdmin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: {
        first_name: firstName || "",
        last_name: lastName || "",
        phone: phone || "",
        user_type: userType,
      },
    });

    if (authError || !authData.user) {
      return NextResponse.json({ error: authError?.message || "Failed to create authentication user." }, { status: 400 });
    }

    const authUserId = authData.user.id;

    // 2. Fetch or update public.users record (created via trigger or insert if needed)
    let domainUser: any = null;
    const { data: existingUser } = await supabaseAdmin
      .from("users")
      .select("id, email, user_type")
      .eq("auth_user_id", authUserId)
      .maybeSingle();

    if (existingUser) {
      const { data: updated } = await supabaseAdmin
        .from("users")
        .update({
          user_type: userType,
          status: "active",
          phone: phone || null,
        })
        .eq("id", existingUser.id)
        .select()
        .single();
      domainUser = updated;
    } else {
      const { data: created, error: createErr } = await supabaseAdmin
        .from("users")
        .insert({
          auth_user_id: authUserId,
          email,
          user_type: userType,
          phone: phone || null,
          status: "active",
        })
        .select()
        .single();

      if (createErr) {
        return NextResponse.json({ error: createErr.message }, { status: 500 });
      }
      domainUser = created;
    }

    // 3. Link specified role in user_roles
    if (domainUser && role) {
      const { data: roleRecord } = await supabaseAdmin
        .from("roles")
        .select("id")
        .eq("name", role)
        .maybeSingle();

      if (roleRecord) {
        await supabaseAdmin.from("user_roles").upsert({
          user_id: domainUser.id,
          role_id: roleRecord.id,
        });
      }
    }

    return NextResponse.json({
      success: true,
      user: {
        id: domainUser.id,
        email: domainUser.email,
        user_type: domainUser.user_type,
        role,
        temp_password: password,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error." }, { status: 500 });
  }
}
