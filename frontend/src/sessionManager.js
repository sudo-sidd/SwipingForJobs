// Session management utility for handling authentication
class SessionManager {
    constructor() {
        this.tokenKey = 'swipingforjobs_session_token';
        this.userKey = 'swipingforjobs_user_data';
        this.expiryKey = 'swipingforjobs_session_expiry';
    }

    // Store session data
    setSession(sessionToken, userData, expiresAt) {
        try {
            if (!sessionToken || !userData || !expiresAt) {
                console.error('Invalid session data provided');
                return false;
            }
            
            localStorage.setItem(this.tokenKey, sessionToken);
            localStorage.setItem(this.userKey, JSON.stringify(userData));
            localStorage.setItem(this.expiryKey, expiresAt);
            
            console.log('Session data stored successfully');
            return true;
        } catch (error) {
            console.error('Error storing session data:', error);
            return false;
        }
    }

    // Get session token
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    // Get user data
    getUser() {
        try {
            const userData = localStorage.getItem(this.userKey);
            if (!userData) return null;
            
            const parsed = JSON.parse(userData);
            
            // Validate that we have essential user data
            if (!parsed || !parsed.id || !parsed.email) {
                console.warn('Invalid user data in session');
                return null;
            }
            
            return parsed;
        } catch (error) {
            console.error('Error parsing user data:', error);
            return null;
        }
    }

    // Get session expiry
    getExpiry() {
        return localStorage.getItem(this.expiryKey);
    }

    // Check if session is valid
    isSessionValid() {
        const token = this.getToken();
        const expiry = this.getExpiry();
        const user = this.getUser();
        
        if (!token || !expiry || !user) {
            return false;
        }

        try {
            const expiryDate = new Date(expiry);
            const now = new Date();
            
            // Check if the date is valid and not expired
            if (isNaN(expiryDate.getTime())) {
                console.warn('Invalid expiry date in session')
                return false;
            }
            
            return now < expiryDate;
        } catch (error) {
            console.error('Error checking session validity:', error);
            return false;
        }
    }

    // Clear session data
    clearSession() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.expiryKey);
    }

    // Get authorization headers for API calls
    getAuthHeaders() {
        const token = this.getToken();
        if (!token) {
            return {};
        }

        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    // Update user data in session
    updateUser(userData) {
        localStorage.setItem(this.userKey, JSON.stringify(userData));
    }

    // Check if user is logged in
    isLoggedIn() {
        return this.isSessionValid() && this.getUser() !== null;
    }

    // Auto-refresh session if it's close to expiring
    async checkAndRefreshSession() {
        const token = this.getToken()
        const user = this.getUser()
        
        if (!token || !user) {
            console.log('No token or user data found')
            this.clearSession()
            return false
        }
        
        if (!this.isSessionValid()) {
            console.log('Local session validation failed')
            this.clearSession()
            return false
        }

        try {
            // Verify session with server
            const response = await fetch('http://localhost:8000/auth/me', {
                method: 'GET',
                headers: this.getAuthHeaders()
            })

            if (response.ok) {
                const data = await response.json()
                console.log('Session verified with server successfully')
                
                // Update user data in session to keep it fresh
                this.updateUser(data.user)
                
                // Check if session is close to expiring and refresh if needed
                const expiry = this.getExpiry()
                if (expiry) {
                    const expiryDate = new Date(expiry)
                    const now = new Date()
                    const timeUntilExpiry = expiryDate.getTime() - now.getTime()
                    
                    // If session expires in less than 2 hours, refresh it
                    if (timeUntilExpiry < 2 * 60 * 60 * 1000) {
                        console.log('Session close to expiring, refreshing...')
                        try {
                            const refreshResponse = await fetch('http://localhost:8000/auth/refresh', {
                                method: 'POST',
                                headers: this.getAuthHeaders()
                            })

                            if (refreshResponse.ok) {
                                const refreshData = await refreshResponse.json()
                                const currentUser = this.getUser()
                                this.setSession(refreshData.session.token, currentUser, refreshData.session.expires_at)
                                console.log('Session refreshed successfully')
                            } else {
                                console.warn('Failed to refresh session, will retry later')
                            }
                        } catch (refreshError) {
                            console.warn('Session refresh failed due to network error:', refreshError)
                            // Don't fail the session check for network errors during refresh
                        }
                    }
                }
                
                return true
            } else if (response.status === 401) {
                console.log('Session verification failed: unauthorized')
                this.clearSession()
                return false
            } else {
                console.warn('Session verification failed with status:', response.status)
                // For other errors, assume session is still valid unless it's expired locally
                return this.isSessionValid()
            }
        } catch (error) {
            console.error('Failed to verify session due to network error:', error)
            // Don't clear session on network errors, might be temporary
            // Just check local expiration
            return this.isSessionValid()
        }
    }

    // Get time until session expires in minutes
    getTimeUntilExpiry() {
        const expiry = this.getExpiry()
        if (!expiry) return 0
        
        const expiryDate = new Date(expiry)
        const now = new Date()
        const timeUntilExpiry = expiryDate.getTime() - now.getTime()
        
        return Math.max(0, Math.floor(timeUntilExpiry / (1000 * 60)))
    }

    // Check if session expires soon (less than 30 minutes)
    isSessionExpiringSoon() {
        return this.getTimeUntilExpiry() < 30
    }
}

// Create singleton instance
const sessionManager = new SessionManager();

export default sessionManager;
