import React from 'react';

const Sidebar: React.FC = () => {
    return (
        <aside style={{ width: '200px', borderRight: '1px solid #eee', height: 'calc(100vh - 60px)' }}>
            <ul style={{ listStyle: 'none', padding: '20px' }}>
                <li style={{ marginBottom: '10px', color: '#007bff' }}>Dashboard</li>
                <li style={{ marginBottom: '10px' }}>Users</li>
                <li style={{ marginBottom: '10px' }}>Settings</li>
            </ul>
        </aside>
    );
};

export default Sidebar;
