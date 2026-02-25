import React from 'react';
// TODO: Import the Typeahead component and integrate it here
// import Typeahead from './Typeahead';

const Navbar: React.FC = () => {
    return (
        <nav style={{
            height: '60px',
            borderBottom: '1px solid #ccc',
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            justifyContent: 'space-between'
        }}>
            <div className="logo" style={{ fontWeight: 'bold' }}>Enterprise Dashboard</div>

            <div className="nav-search">
                {/* TODO: Place the Typeahead component here */}
                <div style={{ color: '#666', fontSize: '14px' }}>Search placeholder...</div>
            </div>

            <div className="user-profile">Admin</div>
        </nav>
    );
};

export default Navbar;
