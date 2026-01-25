// This function determines the API URL based on where you are accessing the dashboard
const getApiBase = () => {
    // Check if we are running in the browser
    if (typeof window !== 'undefined') {
        // Uses the current IP/Domain from the address bar and points to port 8001
        return `http://${window.location.hostname}:8001/api/v1`;
    }
    // Fallback for Server-Side Rendering (using the Docker internal service name)
    return 'http://vanna-api:8001/api/v1';
};

const API_BASE = getApiBase();

export async function fetchStats() {
    const res = await fetch(`${API_BASE}/learning/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function fetchDetailedStats() {
    const res = await fetch(`${API_BASE}/learning/detailed`);
    if (!res.ok) throw new Error('Failed to fetch detailed stats');
    return res.json();
}

export async function fetchPatterns(type = null) {
    const url = type ? `${API_BASE}/learning/patterns?pattern_type=${type}` : `${API_BASE}/learning/patterns`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch patterns');
    return res.json();
}

export async function fetchConversations(limit = 10) {
    const res = await fetch(`${API_BASE}/conversation/history?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch conversations');
    return res.json();
}

export async function fetchDatabaseTables() {
    const res = await fetch(`${API_BASE}/database/tables`);
    if (!res.ok) throw new Error('Failed to fetch database tables');
    return res.json();
}

export async function fetchMemory(limit = 100) {
    const res = await fetch(`${API_BASE}/memory/all?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch memory');
    return res.json();
}