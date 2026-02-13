module.exports = {
  apps: [
    {
      name: "torrent-to-drive",
      script: "venv/bin/python",
      args: "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000",
      cwd: "/home/rahul/torrent-to-drive",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
      },
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/pm2-error.log",
      out_file: "logs/pm2-out.log",
      merge_logs: true,
    },
  ],
};
