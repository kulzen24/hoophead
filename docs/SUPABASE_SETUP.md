# Supabase Setup Guide for HoopHead

## 🎯 Overview
This guide walks you through setting up Supabase as your PostgreSQL database for the HoopHead project.

## 📋 Prerequisites
- Supabase account (free tier is sufficient for development)
- Access to your project's `.env` file

## 🚀 Step 1: Create Supabase Project

1. **Visit [supabase.com](https://supabase.com)**
2. **Sign up or log in**
3. **Click "New Project"**
4. **Configure your project:**
   - **Organization**: Select or create
   - **Name**: `hoophead`
   - **Database Password**: Choose a strong password (save this!)
   - **Region**: Select the region closest to you
   - **Pricing Plan**: Free (sufficient for development)

5. **Click "Create new project"**
6. **Wait 2-3 minutes** for project initialization

## 🔑 Step 2: Get Your Credentials

Once your project is ready:

1. **Go to Settings > API** in your Supabase dashboard
2. **Copy the following values:**

### Project URL
```
https://your-project-ref.supabase.co
```

### Anon/Public Key (for client-side access)
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Service Role Key (for server-side access)
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Database URL
Go to **Settings > Database** and find:
```
postgresql://postgres:[YOUR_PASSWORD]@db.your-project-ref.supabase.co:5432/postgres
```

## ⚙️ Step 3: Configure Environment Variables

1. **Create `.env` file** in your project root:

```bash
cp .env.example .env
```

2. **Update `.env` with your Supabase credentials:**

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-public-key-here
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.your-project-ref.supabase.co:5432/postgres

# Rest of your environment variables...
```

## 🗄️ Step 4: Create Database Schema

### Option A: Using Supabase Dashboard

1. **Go to Table Editor** in your Supabase dashboard
2. **Create tables manually** using the SQL editor

### Option B: Using Migration Scripts (Recommended)

1. **Create our initial schema** (we'll do this next in the project)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create basketball schema
CREATE SCHEMA basketball;
CREATE SCHEMA users;
CREATE SCHEMA queries;

-- Set search path
ALTER DATABASE postgres SET search_path TO public, basketball, users, queries;
```

## 🔐 Step 5: Configure Row Level Security (Optional)

For production, enable RLS:

1. **Go to Authentication > Policies**
2. **Enable RLS** for sensitive tables
3. **Create policies** as needed

## ✅ Step 6: Test Connection

You can test your connection using the Supabase client:

```python
from supabase import create_client, Client

url = "https://your-project-ref.supabase.co"
key = "your-anon-key"
supabase: Client = create_client(url, key)

# Test connection
response = supabase.table('test').select("*").execute()
print("Connection successful!")
```

## 🛠️ Development vs Production

### Development Setup
- Use **anon key** for frontend
- Use **service role key** for backend (never expose this!)
- Enable **email confirmations** disabled for easier testing

### Production Setup
- Enable **Row Level Security (RLS)**
- Configure **email templates**
- Set up **custom domains** if needed
- Configure **webhooks** for events

## 📊 Monitoring & Maintenance

### Database Usage
- Monitor your database usage in **Settings > Usage**
- Free tier includes:
  - 500MB database space
  - 2GB bandwidth
  - 50MB file storage

### Backups
- Supabase automatically backs up your database
- You can also create manual backups in **Settings > Database**

## 🚨 Troubleshooting

### Common Issues

1. **Connection timeouts**
   - Check your internet connection
   - Verify database URL is correct
   - Ensure password doesn't contain special characters that need encoding

2. **Permission denied**
   - Make sure you're using the correct key for your use case
   - Check if RLS is blocking your queries

3. **SSL/TLS errors**
   - Supabase requires SSL connections
   - Make sure your connection string includes SSL parameters

### Getting Help

- **Supabase Discord**: [discord.supabase.com](https://discord.supabase.com)
- **Documentation**: [supabase.com/docs](https://supabase.com/docs)
- **GitHub Issues**: [github.com/supabase/supabase](https://github.com/supabase/supabase)

## 🔄 Next Steps

After completing this setup:

1. ✅ Update your `.env` file with Supabase credentials
2. ✅ Test the connection
3. ➡️ Create database schema for basketball data
4. ➡️ Implement NBA API integration
5. ➡️ Set up data models and repositories

## 📝 Notes

- **Free tier limitations**: Monitor your usage to avoid overages
- **Security**: Never commit `.env` files to version control
- **Scaling**: Supabase can scale with your project from free to enterprise
- **Features**: Supabase provides real-time subscriptions, auth, storage, and more beyond just PostgreSQL 