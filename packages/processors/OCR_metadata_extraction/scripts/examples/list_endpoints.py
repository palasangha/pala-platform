import re
import os

#routes_dir = "/mnt/sda1/mango1_home/gvpocr/backend/app/routes"
routes_dir = "/mnt/sda1/mango1_home/gvpocr/backend/app/routes"
endpoints = {}

for filename in sorted(os.listdir(routes_dir)):
    if filename.endswith('.py') and filename != '__init__.py':
        filepath = os.path.join(routes_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Find blueprint name
        bp_match = re.search(r'(\w+)_bp\s*=\s*Blueprint', content)
        if bp_match:
            bp_name = bp_match.group(1)
            prefix = f"/api/{bp_name}" if bp_name != "bulk" else "/api/bulk"
        else:
            continue
            
        # Find all routes
        route_pattern = r'@\w+_bp\.route\([\'"]([^\'"]+)[\'"]\s*,\s*methods=\[([^\]]+)\]\)'
        matches = re.finditer(route_pattern, content)
        
        if bp_name not in endpoints:
            endpoints[bp_name] = {"prefix": prefix, "routes": []}
            
        for match in matches:
            path = match.group(1)
            methods = match.group(2)
            methods = [m.strip().strip("'\"") for m in methods.split(',')]
            full_path = prefix + path
            endpoints[bp_name]["routes"].append({
                "path": full_path,
                "methods": methods
            })

# Print formatted output
for bp_name in sorted(endpoints.keys()):
    print(f"\n{'='*70}")
    print(f"BLUEPRINT: {bp_name.upper()}")
    print(f"{'='*70}")
    for route in endpoints[bp_name]["routes"]:
        methods_str = " | ".join(route["methods"])
        print(f"  [{methods_str:20}] {route['path']}")

