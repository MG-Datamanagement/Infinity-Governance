import DatasetListPage from "@/app/(data-connectors)/components/DatasetListPage";

interface Props {
    params: { sourceId: string };
}

export default function Page({ params }: Props) {
    return <DatasetListPage sourceId={params.sourceId} />;
}
