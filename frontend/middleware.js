import { NextResponse } from 'next/server';

export function middleware(request) {
  const token = request.cookies.get('sb-access-token')?.value;
  const { pathname } = request.nextUrl;

  // Allow requests to /login
  if (pathname === '/login') {
    if (token) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  // Protect all other routes
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    // Remember where the user was heading so we can redirect them back
    loginUrl.searchParams.set('redirect', pathname + request.nextUrl.search);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images (local public images / logos)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|images).*)',
  ],
};
