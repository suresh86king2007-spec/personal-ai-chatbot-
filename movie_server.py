
import sys
import json
import urllib.parse

def get_movie_link(movie_name):

    movie_name = movie_name.strip()

    if not movie_name:
        return {
            "success": False,
            "message": "Movie name is required."
        }

    query = urllib.parse.quote_plus(
        movie_name
    )

    # Safe legal search URL
    search_url = (
        "https://www.google.com/search?q="
        + query
        + "+movie+official"
    )

    return {
        "success": True,
        "movie": movie_name,
        "link": search_url
    }


def main():

    for line in sys.stdin:

        line = line.strip()

        if not line:
            continue

        try:

            request = json.loads(line)

            method = request.get(
                "method"
            )

            if method == "get_movie_link":

                movie_name = request.get(
                    "movie_name",
                    ""
                )

                result = get_movie_link(
                    movie_name
                )

            elif method == "list_tools":

                result = {
                    "tools": [
                        "get_movie_link"
                    ]
                }

            elif method == "ping":

                result = {
                    "success": True,
                    "message": "Movie MCP server is running."
                }

            else:

                result = {
                    "success": False,
                    "message": "Unknown method."
                }

            print(
                json.dumps(result),
                flush=True
            )

        except Exception as e:

            print(
                json.dumps({
                    "success": False,
                    "message": str(e)
                }),
                flush=True
            )


if __name__ == "__main__":
    main()
