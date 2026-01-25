'use client';
import { useState } from 'react';
import DatabaseView from './DatabaseView';
import ToolUsageView from './ToolUsageView';
import MemoryView from './MemoryView';

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('overview');

    const renderContent = () => {
        switch (activeTab) {
            case 'database':
                return <DatabaseView />;
            case 'memory':
                return <MemoryView />;
            case 'tools':
                return <ToolUsageView />;
            case 'overview':
            default:
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Welcome to Vanna Agent Dashboard</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <DashboardCard
                                title="Agent Memory"
                                description="View what's stored in ChromaDB (Agent Memory)."
                                onClick={() => setActiveTab('memory')}
                            />
                            <DashboardCard
                                title="Tool Usage"
                                description="Monitor tool usage frequency and success rates."
                                onClick={() => setActiveTab('tools')}
                            />
                            <DashboardCard
                                title="Database Tables"
                                description="See tables in the connected database."
                                onClick={() => setActiveTab('database')}
                            />
                        </div>
                    </div>
                );
        }
    };

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100 font-sans">
            <nav className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex h-16 justify-between items-center">
                        <div className="flex items-center">
                            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent cursor-pointer" onClick={() => setActiveTab('overview')}>
                                Vanna AI Dashboard
                            </h1>
                        </div>
                        <div className="hidden sm:flex sm:space-x-8">
                            <NavBarItem label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
                            <NavBarItem label="Memory" active={activeTab === 'memory'} onClick={() => setActiveTab('memory')} />
                            <NavBarItem label="Tools" active={activeTab === 'tools'} onClick={() => setActiveTab('tools')} />
                            <NavBarItem label="Database" active={activeTab === 'database'} onClick={() => setActiveTab('database')} />
                            <NavBarItem label="Vanna Web UI" active={false} onClick={() => window.open(`//${window.location.hostname}:8001`, '_blank')} />
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    {renderContent()}
                </div>
            </main>
        </div>
    );
}

function NavBarItem({ label, active, onClick }) {
    return (
        <button
            onClick={onClick}
            className={`inline-flex items-center border-b-2 px-1 pt-1 text-sm font-medium transition-colors ${active
                    ? 'border-blue-500 text-zinc-900 dark:text-white'
                    : 'border-transparent text-zinc-500 hover:border-zinc-300 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-300'
                }`}
        >
            {label}
        </button>
    );
}

function DashboardCard({ title, description, onClick }) {
    return (
        <div
            onClick={onClick}
            className="cursor-pointer overflow-hidden rounded-lg bg-white dark:bg-zinc-900 shadow hover:shadow-md transition-shadow duration-200 border border-zinc-200 dark:border-zinc-800 p-6"
        >
            <h3 className="text-lg font-medium leading-6 text-zinc-900 dark:text-zinc-100">{title}</h3>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
            <div className="mt-4">
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500">
                    View details &rarr;
                </span>
            </div>
        </div>
    );
}
