# 🎯 Next Step: Initialize Database Schema

## Current Status

✅ Backend API deployed and running
✅ Database connection working (pegasus_user/pegasus_db)
✅ Mobile app configured to use production API
⚠️  **Database tables not created yet**

## What's Missing

The database exists but the tables (courses, lectures, jobs, artifacts, threads, exports) haven't been created yet. This is why the API returns empty arrays for `/courses` and `/lectures`.

## Run This Now

```bash
./scripts/init-database-schema.sh
```

This will:
1. Connect to the Cloud SQL instance (planwell-db)
2. Use the pegasus_db database (separate from planwell database)
3. Create all necessary tables
4. Create indexes for performance

**You'll need valid `pegasus_user` credentials available in your environment (do not place plaintext passwords in docs or shell history).**

## After Schema is Created

Then you can test the full end-to-end flow:

1. **Start mobile app:**
   ```bash
   cd mobile
   npx expo start --clear
   ```

2. **Test record button** - Open app on physical device and try recording

3. **Test upload flow** - Record → Upload → Check backend logs

4. **Verify data** - Check if lecture appears in database:
   ```bash
   curl https://pegasus-api-988514135894.us-west1.run.app/lectures
   ```

## Database Info

- **Instance:** planwell-db (shared with other apps)
- **Database:** pegasus_db (dedicated to Pegasus)
- **User:** pegasus_user
- **Location:** us-central1

This setup is correct - multiple apps can share one Cloud SQL instance with separate databases. This saves costs while keeping data isolated.
