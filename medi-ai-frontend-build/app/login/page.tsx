import { readFileSync } from 'fs'
import { join } from 'path'

export default function LoginPage() {
  const htmlContent = readFileSync(join(process.cwd(), 'public', 'login.html'), 'utf-8')
  
  return (
    <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
  )
}
