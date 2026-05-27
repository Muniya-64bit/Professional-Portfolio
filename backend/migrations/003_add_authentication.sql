-- Add password authentication to user table
ALTER TABLE "user" ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE "user" ADD COLUMN full_name VARCHAR(150);
