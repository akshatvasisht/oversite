import React, { useState, useEffect } from 'react';
import { mockFetchUsers } from '../api';

const Typeahead: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<string[]>([]);

    useEffect(() => {
        // TODO: Implement debounced search logic
    }, [query]);

    return (
        <div className="typeahead" style={{ position: 'relative' }}>
            <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search users..."
                style={{ padding: '5px 10px', width: '250px' }}
            />
            {/* TODO: Render dropdown results */}
        </div>
    );
};

export default Typeahead;
