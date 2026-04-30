from django.http import HttpResponse


class CORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
            self.add_cors_headers(response)
            return response

        response = self.get_response(request)
        self.add_cors_headers(response)
        return response

    @staticmethod
    def add_cors_headers(response: HttpResponse) -> HttpResponse:
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
