import createMDX from '@next/mdx';

/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
};

const withMDX = createMDX({
  extension: /\.mdx?$/,
  options: {
    // You can add remark/rehype plugins here if needed
  }
});

export default withMDX(nextConfig);