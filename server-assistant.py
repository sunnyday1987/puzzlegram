from http.server import BaseHTTPRequestHandler, HTTPServer
from requests_toolbelt.multipart import decoder
import json
import os
from openai import OpenAI


# Set your OpenAI API key here
client = OpenAI(
    api_key=os.environ['OPENAI_KEY']
)


my_assistant = client.beta.assistants.create(
    model="gpt-4o",
    instructions="Retain all information that is shared by the person sharing information about themselves. Call out any discrepancies in the information I share.",
    name="Puzzlegram",
    tools=[{"type": "file_search"}],
)

# my_assistant = client.beta.assistants.retrieve('asst_HzqAe5cmOg7iUVWF0k18RYFR')

# my_thread = client.beta.threads.retrieve('thread_GZ4W2kVBonyLOWVniOVJiqX9')
my_thread = client.beta.threads.create()


def create_message(text):
    my_message = client.beta.threads.messages.create(
      thread_id=my_thread.id,
      role="user",
      content=text,
    )
    return my_message


def create_run_and_poll():
    return client.beta.threads.runs.create_and_poll(
      thread_id=my_thread.id,
      assistant_id=my_assistant.id,
      # instructions="Please address the user as Sunny."
    )


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as file:
                self.wfile.write(file.read())


    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Allow-Origin')
        self.end_headers()

        if self.path == '/':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
 
            # Parse JSON data from the request
            request_data = json.loads(post_data.decode('utf-8'))

            # Get the prompt from the request
            prompt = request_data['prompt']
            # file_url = request_data.get('file_url')
            image_url = request_data.get('image_url')
            if image_url:
                response = client.chat.completions.create(
                  model="gpt-4o",
                  messages=[
                    {
                      "role": "user",
                      "content": [
                        {"type": "text", "text": prompt},
                        {
                          "type": "image_url",
                          "image_url": {
                            "url": image_url,
                          },
                        },
                      ],
                    }
                  ],
                  max_tokens=300,
                )
                response_message = response.choices[0].message.content
            else:
                # Send prompt to OpenAI for completion
                create_message(prompt)
                response = create_run_and_poll()
                messages = client.beta.threads.messages.list(
                  thread_id=my_thread.id
                )
                response_message = messages.data[0].content[0].text.value

            # Send completion as JSON response
            self.wfile.write(json.dumps({
                'completion': response_message,
            }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Allow-Origin')
        self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    run()
