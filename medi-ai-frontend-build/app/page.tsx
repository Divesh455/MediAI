import { readFileSync } from 'fs'
import { join } from 'path'

export default function Home() {
  const htmlContent = readFileSync(join(process.cwd(), 'public', 'index.html'), 'utf-8')
  
  return (
    <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
  )
}
