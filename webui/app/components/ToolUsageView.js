'use client';
import { useState, useEffect } from 'react';
import { fetchDetailedStats } from '../lib/api';

export default function ToolUsageView() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchDetailedStats()
            .then(data => {
                setStats(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="p-4 text-zinc-500">Loading stats...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

    const { total_successful_queries, total_tool_success, total_tool_failure, success_rate, example_tool_patterns } = stats;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard title="Successful Queries" value={total_successful_queries} />
                <StatCard title="Tool Successes" value={total_tool_success} />
                <StatCard title="Tool Failures" value={total_tool_failure} />
                <StatCard title="Success Rate" value={`${(success_rate * 100).toFixed(1)}%`} />
            </div>

            <div className="space-y-4">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Common Tool Patterns</h2>
                <div className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
                    {(!example_tool_patterns || example_tool_patterns.length === 0) ? (
                        <div className="p-4 text-zinc-500">No tool usage patterns learned yet.</div>
                    ) : (
                        <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
                            {example_tool_patterns.map((pattern, idx) => (
                                <div key={idx} className="p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                            {pattern.tool_name}
                                        </span>
                                        <span className="text-xs text-zinc-500">
                                            Used {pattern.success_count} times
                                        </span>
                                    </div>
                                    <div className="text-sm">
                                        <span className="font-semibold text-zinc-600 dark:text-zinc-400">Pattern: </span>
                                        <code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded text-zinc-800 dark:text-zinc-200">
                                            {pattern.question_pattern}
                                        </code>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({ title, value }) {
    return (
        <div className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
            <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{title}</h3>
            <p className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{value}</p>
        </div>
    );
}
