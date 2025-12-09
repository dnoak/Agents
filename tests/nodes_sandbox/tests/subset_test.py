x = {'a', 'b', 'c'}
y = {'a':1, 'b':2}
z = {'a':1, 'b':2, 'c': 4}
w = {'a':1, 'b':2, 'c': 5, 'd': 6}

print(x.issubset(y.keys()))
print(x.issubset(z.keys()))
print(x.issubset(w.keys()))