import { createClerkClient } from '@clerk/backend';

async function test() {
  console.log('SECRET_KEY:', process.env.CLERK_SECRET_KEY?.substring(0, 30) + '...');
  console.log('Creating client...');
  
  const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });
  
  console.log('Calling testingTokens.createTestingToken()...');
  
  try {
    const result = await clerk.testingTokens.createTestingToken();
    console.log('✓ Success!');
    console.log('Token (first 20 chars):', result.token?.substring(0, 20));
  } catch (error) {
    console.error('✗ Error:', error.message);
    console.error('Status:', error.status);
    console.error('Errors:', error.errors);
  }
}

test();
