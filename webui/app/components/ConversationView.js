'use client';
import { useState, useEffect } from 'react';
import { fetchConversations } from '../lib/api';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export default function ConversationView() {
    const [conversations, setConversations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchConversations()
            .then(data => {
                setConversations(data.conversations || []);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="p-4 text-zinc-500">Loading conversations...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Recent Conversations</h2>
            <div className="space-y-4">
                {conversations.length === 0 ? (
                    <div className="p-4 border rounded-md text-zinc-500 dark:border-zinc-800">No conversations found.</div>
                ) : (
                    conversations.map((conv, idx) => (
                        <div key={idx} className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden shadow-sm">
                            <div className="bg-zinc-50 dark:bg-zinc-800/50 px-4 py-2 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center">
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                                        {conv.username || conv.user_id}
                                    </span>
                                    <span className="text-xs text-zinc-500">
                                        {conv.timestamp ? new Date(conv.timestamp).toLocaleString() : ''}
                                    </span>
                                </div>
                                <div className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                    {conv.conversation_id}
                                </div>
                            </div>

                            <div className="p-4 space-y-3">
                                <div>
                                    <div className="text-xs font-semibold text-zinc-400 mb-1 uppercase tracking-wider">User</div>
                                    <div className="text-sm text-zinc-800 dark:text-zinc-200 bg-blue-50 dark:bg-blue-900/20 p-2 rounded-md border border-blue-100 dark:border-blue-900/30">
                                        {conv.question}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-xs font-semibold text-zinc-400 mb-1 uppercase tracking-wider">Agent</div>
                                    <div className="text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
                                        {conv.response}
                                    </div>
                                </div>

                                {conv.metadata?.chart && (
                                    <div className="mt-4 border border-zinc-200 dark:border-zinc-700 rounded-lg p-2 bg-white">
                                        <div className="text-xs font-semibold text-zinc-400 mb-1 uppercase tracking-wider">Chart</div>
                                        <Plot
                                            data={conv.metadata.chart.data}
                                            layout={{ ...conv.metadata.chart.layout, autosize: true }}
                                            style={{ width: "100%", height: "400px" }}
                                            useResizeHandler={true}
                                        />
                                    </div>
                                )}

                                {conv.metadata && (
                                    <div className="mt-2 text-xs text-zinc-400 font-mono">
                                        <details>
                                            <summary className="cursor-pointer hover:text-zinc-600 dark:hover:text-zinc-300">Raw Metadata</summary>
                                            <pre className="mt-1 whitespace-pre-wrap overflow-x-auto">
                                                {JSON.stringify(conv.metadata, (key, value) => {
                                                    if (key === 'chart') return '[Chart Data]';
                                                    return value;
                                                }, 2)}
                                            </pre>
                                        </details>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
