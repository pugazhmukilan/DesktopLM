

def createFile(filename, content):
    """Creates a file with the given filename and writes the specified content to it."""
    with open(filename, 'w') as file:
        file.write(content)