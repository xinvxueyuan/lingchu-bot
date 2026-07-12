import { llms } from "fumadocs-core/source";
import { source } from "@/lib/source";

export const revalidate = false;

export async function GET() {
  return new Response(llms(source).index());
}
