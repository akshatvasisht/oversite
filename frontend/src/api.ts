import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api/v1',
});

// Interceptor to add X-Session-ID if it exists in localStorage
api.interceptors.request.use((config) => {
    const sessionId = localStorage.getItem('sessionId');
    if (sessionId) {
        config.headers['X-Session-ID'] = sessionId;
    }
    return config;
});

export default api;
