import React from 'react';
import Layout from './components/Layout';

const App: React.FC = () => {
    return (
        <Layout>
            <h2>User Management</h2>
            <p>Select a user from the global search in the navbar above to get started.</p>
        </Layout>
    );
};

export default App;
