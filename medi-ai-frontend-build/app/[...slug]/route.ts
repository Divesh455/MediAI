import { readFileSync } from 'fs'
import { join } from 'path'
import { NextResponse } from 'next/server'

export async function GET(request: Request, { params }: { params: { slug?: string[] } }) {
  try {
    const path = params.slug ? params.slug.join('/') : 'index'
    const filePath = join(process.cwd(), 'public', `${path}.html`)
    
    const content = readFileSync(filePath, 'utf-8')
    return new NextResponse(content, {
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
      },
    })
  } catch (error) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }
}
