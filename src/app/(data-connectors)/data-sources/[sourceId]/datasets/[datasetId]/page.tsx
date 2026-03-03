import DatasetDetailPage from "@/app/(data-connectors)/components/DatasetDetailPage";

interface Props {
    params: { sourceId: string; datasetId: string };
}

export default function Page({ params }: Props) {
    return <DatasetDetailPage sourceId={params.sourceId} datasetId={params.datasetId} />;
}
