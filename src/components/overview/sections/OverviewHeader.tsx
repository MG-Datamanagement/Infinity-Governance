/**
 * OverviewHeader
 *
 * Top action bar for the Overview page.
 * Extracted so it can be independently tested, styled, or replaced
 * without touching page layout or data concerns.
 */

export function OverviewHeader() {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
      <p className="text-sm text-gray-600">
        Monitor your data governance health and activities
      </p>

      {/* <div className="flex items-center gap-2">
        <Button icon={<Database size={16} />}>Add Data Source</Button>
        <Select placeholder="Quick Actions" options={QUICK_ACTIONS} />
      </div> */}
    </div>
  );
}
