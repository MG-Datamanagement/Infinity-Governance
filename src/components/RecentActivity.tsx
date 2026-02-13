const RecentActivity = () => {
    return (
        <>
            {/* Recent Activity */}
            <div className="xl:col-span-4">
                <ErrorBoundary>
                    <div className="card overflow-hidden h-full flex flex-col">
                        <div className="p-2 md:p-4 border-b border-gray-200">
                            {/* <div className="flex items-center justify-between mb-4">
                              <h3 className="font-semibold text-gray-900">Recent Activity</h3>
                            </div> */}

                            {/* Tabs */}
                            <div className="flex gap-4 border-b border-gray-200">
                                <button
                                    onClick={() => setActivityTab('recent')}
                                    className={cn(
                                        'pb-2 px-1 text-sm font-medium border-b-2 transition-colors flex items-center gap-2',
                                        activityTab === 'recent'
                                            ? 'text-primary border-primary'
                                            : 'text-gray-500 border-transparent hover:text-gray-700'
                                    )}
                                >
                                    <Clock size={16} />
                                    Recent Activity
                                </button>
                                <button
                                    onClick={() => setActivityTab('viewed')}
                                    className={cn(
                                        'pb-2 px-1 text-sm font-medium border-b-2 transition-colors flex items-center gap-2',
                                        activityTab === 'viewed'
                                            ? 'text-primary border-primary'
                                            : 'text-gray-500 border-transparent hover:text-gray-700'
                                    )}
                                >
                                    <BarChart2 size={16} />
                                    Recently Viewed
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            <div className="divide-y divide-gray-100">
                                {!activityLoading && activity && activity.slice(0, 10).map((item) => (
                                    <div key={item.id} className="px-4 md:px-6 py-3 hover:bg-gray-50 cursor-pointer">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
                                                <Database size={14} className="text-purple-600" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-medium text-gray-900 truncate">
                                                    {item.name}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {item.type} • {item.table}
                                                </div>
                                            </div>
                                            <div className="text-xs text-gray-400 flex-shrink-0">
                                                {item.timestamp}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="p-2 border-t border-gray-200">
                            <button className="text-primary text-sm font-medium hover:underline w-full text-center">
                                View all recently viewed
                            </button>
                        </div>
                    </div>
                </ErrorBoundary>
            </div>
        </>
    )
}