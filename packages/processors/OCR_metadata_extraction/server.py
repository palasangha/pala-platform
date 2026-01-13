#!/usr/bin/env python3
import sys
import argparse
from llama_cpp import Llama
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class ServerHandler(BaseHTTPRequestHandler):
    llm = None
    
    def log_message(self, format, *args):
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), format % args))
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/completion':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                prompt = data.get('prompt', '')
                
                if not self.llm:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Model not loaded"}).encode())
                    return
                
                output = self.llm(prompt, max_tokens=4096, temperature=0.1)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "content": output['choices'][0]['text'],
                    "tokens": output['usage']['completion_tokens']
                }
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model', required=True, help='Path to model file')
    parser.add_argument('--mmproj', help='Path to multimodal projection model file')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()
    
    print(f"Loading model from {args.model}...")
    try:
        kwargs = {'model_path': args.model, 'n_gpu_layers': -1, 'verbose': False}
        if args.mmproj:
            print(f"Using projection model: {args.mmproj}")
            kwargs['mmproj_path'] = args.mmproj
        ServerHandler.llm = Llama(**kwargs)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    server = HTTPServer((args.host, args.port), ServerHandler)
    print(f"Server running on {args.host}:{args.port}")
    server.serve_forever()
