import bcrypt from 'bcryptjs';

export interface User {
  id: string;
  name: string;
  email: string;
  password: string; // hashed
  role: 'admin' | 'user' | 'viewer';
  createdAt: string;
  lastLogin?: string;
}

// Mock user database - In production, this would be a real database
class UserDatabase {
  private users: User[] = [];

  constructor() {
    this.initializeUsers();
  }

  private async initializeUsers() {
    // Create default users with hashed passwords
    const defaultUsers = [
      {
        id: '1',
        name: 'Shivam',
        email: 'shivam@infinity.com',
        password: 'password',
        role: 'admin' as const,
        createdAt: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'Rajkumar S',
        email: 'rajkumar@infinity.com',
        password: 'password123',
        role: 'user' as const,
        createdAt: new Date().toISOString(),
      },
    ];

    for (const user of defaultUsers) {
      const hashedPassword = await bcrypt.hash(user.password, 10);
      this.users.push({
        ...user,
        password: hashedPassword,
      });
    }
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.users.find(u => u.email === email) || null;
  }

  async findById(id: string): Promise<User | null> {
    return this.users.find(u => u.id === id) || null;
  }

  async verifyPassword(plainPassword: string, hashedPassword: string): Promise<boolean> {
    return bcrypt.compare(plainPassword, hashedPassword);
  }

  async createUser(userData: Omit<User, 'id' | 'createdAt' | 'password'> & { password: string }): Promise<User> {
    const hashedPassword = await bcrypt.hash(userData.password, 10);
    const newUser: User = {
      ...userData,
      id: String(this.users.length + 1),
      password: hashedPassword,
      createdAt: new Date().toISOString(),
    };
    this.users.push(newUser);
    return newUser;
  }

  async updateLastLogin(userId: string): Promise<void> {
    const user = this.users.find(u => u.id === userId);
    if (user) {
      user.lastLogin = new Date().toISOString();
    }
  }

  // For development: Get all users (without passwords)
  async getAllUsers(): Promise<Omit<User, 'password'>[]> {
    return this.users.map(({ password, ...user }) => user);
  }
}

// Singleton instance
export const userDb = new UserDatabase();
