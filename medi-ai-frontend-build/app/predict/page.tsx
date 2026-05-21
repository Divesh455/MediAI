import { readFileSync } from 'fs'
import { join } from 'path'

export default function Page() {
  const htmlContent = readFileSync(join(process.cwd(), 'public', 'predict.html'), 'utf-8')
  
  return (
    <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
  )
}
