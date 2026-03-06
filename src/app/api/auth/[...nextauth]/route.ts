import NextAuth, { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { userDb } from '@/lib/auth/userDb';
import { loginSchema } from '@/lib/validations';
import { ZodError } from 'zod';

const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'Email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        try {
          // Validate input with Zod
          const validatedData = loginSchema.parse(credentials);

          // Find user in database
          const user = await userDb.findByEmail(validatedData.email);
          
          if (!user) {
            return null;
          }

          // Verify password
          const isValidPassword = await userDb.verifyPassword(
            validatedData.password,
            user.password
          );

          if (!isValidPassword) {
            return null;
          }

          // Update last login
          await userDb.updateLastLogin(user.id);

          // Return user without password
          return {
            id: user.id,
            name: user.name,
            email: user.email,
            role: user.role,
          };
        } catch (error) {
          if (error instanceof ZodError) {
            // Validation failed
            console.error('Validation error:', error.errors);
            return null;
          }
          console.error('Authentication error:', error);
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: '/login',
    error: '/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = (user as any).role;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
        (session.user as any).role = token.role;
      }
      return session;
    },
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
