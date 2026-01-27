import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import fs from 'fs/promises';
import path from 'path';

async function getDocsContent() {
  const filePath = path.join(process.cwd(), 'app/docs/docs.md');
  const content = await fs.readFile(filePath, 'utf-8');
  return content;
}

export default async function DocsPage() {
  const markdownContent = await getDocsContent();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">API Documentation</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Complete REST API documentation for Vanna AI
            </p>
          </div>
          <div className="p-6 prose prose-lg dark:prose-invert max-w-none text-gray-800 dark:text-gray-200 prose-table:overflow-hidden prose-table:border-collapse prose-table:w-full prose-th:p-4 prose-td:p-4 prose-th:border prose-td:border prose-th:border-gray-300 prose-td:border-gray-300 dark:prose-th:border-gray-600 dark:prose-td:border-gray-600 prose-th:bg-gray-50 dark:prose-th:bg-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {markdownContent}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
