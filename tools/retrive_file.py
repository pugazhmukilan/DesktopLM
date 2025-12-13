def retriveFileContent(filename):
    """Retrieves and returns the content of the specified file."""
    with open(filename, 'r') as file:
        content = file.read()   
        return content  