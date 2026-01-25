'use client';
import { useState, useEffect } from 'react';
import { fetchDatabaseTables } from '../lib/api';

export default function DatabaseView() {
    const [tables, setTables] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchDatabaseTables()
            .then(data => {
                setTables(data.tables || []);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="p-4 text-zinc-500">Loading tables...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Database Tables</h2>
            <div className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
                {tables.length === 0 ? (
                    <div className="p-4 text-zinc-500">No tables found.</div>
                ) : (
                    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                        {tables.map((table, idx) => (
                            <li key={idx} className="p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors flex items-center gap-2">
                                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">📄</span>
                                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{table}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
            <p className="text-sm text-zinc-500">
                Connected MySQL database. These tables are available for the agent to query.
            </p>
        </div>
    );
}
