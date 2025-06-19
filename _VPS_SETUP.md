# VPS-Based Reverse Proxy Solution for Discord Verification

VPS with nginx as a reverse proxy to bypass Cloudflare's complex routing using tunnels.

## Setup Instructions

### Configure nginx as Reverse Proxy

Assuming your config file is `/etc/nginx/sites-available/my-site` with nginx and SSL certificate setup with letsenrypt, and domain pointing to VPS IP address using Ubuntu

Backup existing Nginx configuration
```bash
sudo cp /etc/nginx/sites-available/your-existing-site /etc/nginx/sites-available/your-existing-site.backup
```

Add the location block to your existing site in the server block that has 'listen 443 ssl;'
```bash
    # Discord interaction endpoint configuration
    location /api/interactions {
        proxy_pass http://127.0.0.1:8001;

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout settings (Discord needs quick responses)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
```

Test your configuration
```bash
sudo nginx -t
```

Check symlink exists, otherwise create it `sudo ln -s /etc/nginx/sites-available/my-site /etc/nginx/sites-enabled/`
```bash
ls -l /etc/nginx/sites-enabled/
```

Reload Nginx if the test is successful
```bash
sudo systemctl reload nginx
```

### Setup Reverse Tunnel from Local Machine to VPS

```bash
./connect_to_vps.sh
```

### Verification of the setup by updating Discord application

1. Start your Discord verification server locally on port 8001
```bash
./run_verification.sh
```
2. Establish the SSH tunnel
3. Test:
```bash
curl -I https://your-domain.com/api/interactions
```
4. Update your Discord application in the portal with the new endpoint URL: https://your-domain.com/api/interactions


### View nginx server logs
```bash
sudo tail -f /var/log/nginx/error.log
```

## Advantages Over Cloudflare Tunnel

1. **Direct Control**: No third-party routing or unknown errors
2. **Simplicity**: Standard HTTP(S) connection over SSH tunnel
3. **Debugging**: Full access to both nginx and server logs
4. **Reliability**: SSH tunneling is rock-solid compared to Cloudflare tunnels

## Common Issues and Solutions

### Connection Refused

If you see "Connection refused" errors in nginx logs:

1. Check that your local server is running on port 8001
2. Verify the SSH tunnel is active: `netstat -tuln | grep 8001`
3. Check for firewall issues on VPS: `sudo ufw status`
