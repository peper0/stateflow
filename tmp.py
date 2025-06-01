@reactive(share=lambda x)
def plot(window, label, data):
    print(f"plotting {window} {label}")


window = combo(['a', 'b'])

xx = plot(window, "a", [1, 2])

yy = plot(window, "b", [1, 2])
