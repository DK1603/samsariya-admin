# MongoDB Atlas Setup for Samsariya Bots

## 1. Create MongoDB Atlas Account
1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Sign up for a free account
3. Create a new project called "Samsariya-Bots"

## 2. Create Database Cluster
1. Click "Build a Database"
2. Choose "FREE" tier (M0)
3. Select your preferred cloud provider (AWS/Google Cloud/Azure)
4. Choose a region close to your deployment servers
5. Click "Create"

## 3. Set Up Database Access
1. Go to "Database Access" in the left sidebar
2. Click "Add New Database User"
3. Create a username and password (save these!)
4. Set privileges to "Read and write to any database"
5. Click "Add User"

## 4. Set Up Network Access
1. Go to "Network Access" in the left sidebar
2. Click "Add IP Address"
3. For development: Click "Allow Access from Anywhere" (0.0.0.0/0)
4. For production: Add specific IP addresses of your deployment servers
5. Click "Confirm"

## 5. Get Connection String
1. Go to "Database" in the left sidebar
2. Click "Connect"
3. Choose "Connect your application"
4. Copy the connection string
5. Replace `<password>` with your actual password
6. Replace `<dbname>` with "samsariya"

## 6. Environment Variables
Set these in your deployment environment:
```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/samsariya?retryWrites=true&w=majority
```

## 7. Database Collections Structure
The database will have these collections:
- `orders` - All customer orders
- `inventory` - Menu items and availability
- `admins` - Admin user IDs and permissions
- `config` - Bot configuration settings 