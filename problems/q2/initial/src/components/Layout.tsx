import React from 'react';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return (
        <div className="layout">
            <Navbar />
            <div className="content-wrapper" style={{ display: 'flex' }}>
                <Sidebar />
                <main style={{ flex: 1, padding: '20px' }}>
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;
