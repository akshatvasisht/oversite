import { useState, useEffect } from 'react';

/**
 * Detects and displays an overlay when the user's internet connection is lost.
 */
export default function NetworkStatus() {
    const [isOnline, setIsOnline] = useState(navigator.onLine);

    useEffect(() => {
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    if (isOnline) return null;

    return (
        <div className="network-status-overlay">
            <div className="network-status-modal">
                <h2>Connection Lost</h2>
                <p>We are trying to reconnect to the OverSite network. Please wait...</p>
                <div className="network-loader" />
            </div>
        </div>
    );
}
