# MCP Server Dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy all files
COPY . .

# Install dependencies  
RUN npm install

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Start server
CMD ["npm", "start"]
