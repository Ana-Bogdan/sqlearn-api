from django.conf import settings


def set_auth_cookies(response, access_token: str | None = None, refresh_token: str | None = None) -> None:
    common = {
        "domain": settings.AUTH_COOKIE_DOMAIN,
        "path": settings.AUTH_COOKIE_PATH,
        "secure": settings.AUTH_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
    }

    if access_token is not None:
        response.set_cookie(
            settings.AUTH_COOKIE_ACCESS,
            access_token,
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **common,
        )

    if refresh_token is not None:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh_token,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **common,
        )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(
        settings.AUTH_COOKIE_ACCESS,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.AUTH_COOKIE_REFRESH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
