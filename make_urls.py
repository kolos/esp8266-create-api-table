import glob,re,gzip

libName = 'ESP8266WebServer'
fileList = glob.glob('./*.ino')

def search_for_fn_call(http_server_name, fn_name):
    for fileName in fileList:
        content = open(fileName, 'r', encoding='utf-8').read()
        
        startIdx = content.find(fn_name + '()')
        if startIdx == -1: continue

        endIdx = content.find('}', startIdx)
        fn_content = content[startIdx:endIdx + 1]

        while(fn_content.count('{') != fn_content.count('}')):
            endIdx = content.find('}', endIdx + 1)
            fn_content = content[startIdx:endIdx + 1]
        
        return scan_for_http_args(http_server_name, fn_content)

def scan_for_http_args(http_server_name, content):
    startIdx = 0
    while True:
        startIdx = content.find(http_server_name + '.arg("', startIdx)
        if startIdx == -1: break

        startIdx += len(http_server_name + '.arg("')
        endIdx = content.find('"', startIdx)
        
        yield content[startIdx:endIdx]

def scan_for_http(fileName):
    content = open(fileName, 'r', encoding='utf-8').read()
    for http_server_name in re.findall('ESP8266WebServer\s+(\w+)', content):
        startIdx = 0
        while True:
            startIdx = content.find(http_server_name + '.on', startIdx)
            if startIdx == -1: break
            
            startIdx += len(http_server_name + '.on')           
            endIdx = content.find(');', startIdx)
            fn_call = content[startIdx:endIdx + 2]
            
            while(fn_call.count('(') != fn_call.count(')')):
                endIdx = content.find(');', endIdx + 2)
                fn_call = content[startIdx:endIdx + 2]
                
            first_param_idx = fn_call.find(",")
            first_param = fn_call[2:first_param_idx - 1].strip()

            second_param_idx = fn_call.find(",", first_param_idx +1)
            second_param = fn_call[first_param_idx+1:second_param_idx].strip()

            third_param = fn_call[second_param_idx+1:-2].strip()

            if(third_param.startswith('[]()')):
                yield(first_param, second_param, list(scan_for_http_args(http_server_name, third_param)))
            else:
                yield(first_param, second_param, list(search_for_fn_call(http_server_name, third_param)))

def scan_directory():
    for f in fileList:
        yield scan_for_http(f)

http_param_list = []
http_params_generator = scan_directory()
for http_params in http_params_generator:
    for path, method, args in http_params:
        http_param_list.append((path, method, args))

http_param_list.sort(key=lambda x: x[0])

html = f"""<table border=1 cellspacing=0 cellpadding=3>
<tr>
    <th>Path</th>
    <th>Method</th>
    <th>Arguments</th>
</tr>"""

for path, method, args in http_param_list:
    if method == "HTTP_GET" and len(args) == 0:
        html += f"""
<tr>
    <td><a href="{path}">{path}</a></td>
    <td>{method}</td>
    <td></td>
</tr>"""
    elif method == "HTTP_GET" and len(args) > 0:
        html += f"""
<tr>
    <td>{path}?{'&'.join(x + "=" for x in args)}</a></td>
    <td>{method}</td>
    <td>{' '.join(args)}</td>
</tr>"""
    else:
        html += f"""
<tr>
    <td>{path}</a></td>
    <td>{method}</td>
    <td>{' '.join(args)}</td>
</tr>"""

html += '</table>'
#compressed_html = html.encode('utf8')
compressed_html = gzip.compress(html.encode('utf8'))
# print (len(html), "vs", len(compressed_html))

c_template_file = f"""
PROGMEM const char http_apis_html_content_type[] = "text/html";
PROGMEM const char http_apis_html[] = {{{", ".join([hex(b) for b in compressed_html])}}};
const uint16_t http_apis_html_len = {len(compressed_html)};
"""

print (c_template_file, file=open('http_apis.h', 'w'))