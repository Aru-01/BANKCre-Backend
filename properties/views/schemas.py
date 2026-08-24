from drf_yasg import openapi

def success_schema(description='Success'):
    return openapi.Response(description, openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'data':    openapi.Schema(type=openapi.TYPE_OBJECT),
        },
    ))

def error_schema(description='Error'):
    return openapi.Response(description, openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'errors':  openapi.Schema(type=openapi.TYPE_OBJECT),
        },
    ))
