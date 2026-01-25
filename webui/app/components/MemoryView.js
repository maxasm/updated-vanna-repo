'use client';
import { useState, useEffect } from 'react';
import { fetchMemory } from '../lib/api';

export default function MemoryView() {
    const [memories, setMemories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchMemory()
            .then(data => {
                setMemories(data.memories || []);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="p-4 text-zinc-500">Loading memory...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Agent Memory (ChromaDB)</h2>
            <div className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
                {memories.length === 0 ? (
                    <div className="p-4 text-zinc-500">Memory is empty. Ask some questions to populate it.</div>
                ) : (
                    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                        {memories.map((mem, idx) => (
                            <li key={idx} className="p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="px-2 py-0.5 text-xs font-mono rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 truncate max-w-[200px]">
                                        ID: {mem.id}
                                    </span>
                                    <span className="text-xs text-zinc-400">
                                        {mem.timestamp ? new Date(mem.timestamp).toLocaleString() : 'No timestamp'}
                                    </span>
                                </div>
                                <pre className="text-xs sm:text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap font-mono bg-zinc-50 dark:bg-zinc-950 p-2 rounded border border-zinc-100 dark:border-zinc-800">
                                    {typeof mem.content === 'object'
                                        ? JSON.stringify(mem.content, null, 2)
                                        : mem.content}
                                </pre>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
