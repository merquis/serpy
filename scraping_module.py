import http.client

conn = http.client.HTTPSConnection("api.scrapingant.com")

conn.request("GET", "/v2/general?url=https%3A%2F%2Fexample.com&x-api-key=7970f04a3cff4b9d89a4a287c2cd1ba2")

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
