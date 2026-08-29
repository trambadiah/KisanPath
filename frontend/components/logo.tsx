import Link from "next/link";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="brandLockup" href="/" aria-label="KisanPath home">
      <span className="brandMark" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      {!compact && <span className="brandName">KisanPath</span>}
    </Link>
  );
}
