from Loady import Loady
site_list = [
    "https://www.cnn.com",
    "https://www.amazon.com",
    "https://www.google.com",
    "https://www.facebook.com",
    "https://www.netflix.com"
]

for site in site_list:
    load = Loady(site)
    load.get()
    print(site, ":", load.total_time)