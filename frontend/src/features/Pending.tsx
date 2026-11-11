import { PageHeader } from "@/components/PageHeader";

export function Pending({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <section className="khu rounded-md p-8 text-[15px] text-muc-nhat">Màn hình này đang được hoàn thiện trong bản cập nhật tiếp theo.</section>
    </>
  );
}
