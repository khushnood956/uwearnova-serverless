import AdminEditProductPage from "./AdminEditProductClient";

export function generateStaticParams() {
  return [{ id: "1" }];
}

export default function Page() {
  return <AdminEditProductPage />;
}
