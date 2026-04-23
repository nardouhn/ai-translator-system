import re

res = '<span id="0">Xin chào</span><span id="1" >Thế giới!</span><span id = "2"> Bạn khỏe không? </span>'
pattern = r'<span\s+id\s*=\s*["\']?(\d+)["\']?\s*>(.*?)</span>'
matches = re.findall(pattern, res, flags=re.IGNORECASE | re.DOTALL)
print(matches)
