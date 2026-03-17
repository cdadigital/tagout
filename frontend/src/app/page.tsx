import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl text-center">
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight">
          <span className="text-amber-500">TAGOUT</span>
        </h1>
        <p className="mt-4 text-xl text-gray-400">
          Which unit should you hunt this fall? Get 2025 season predictions for
          Idaho Panhandle elk and deer — powered by 22 years of IDFG data.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/predict"
            className="px-8 py-3 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg transition-colors text-center"
          >
            Check Your Unit
          </Link>
          <Link
            href="/map"
            className="px-8 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors text-center"
          >
            See Unit Rankings
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-3xl font-bold text-amber-500">9</div>
            <div className="text-sm text-gray-500 mt-1">Hunt Units</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-amber-500">22</div>
            <div className="text-sm text-gray-500 mt-1">Years of Data</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-amber-500">R² .94</div>
            <div className="text-sm text-gray-500 mt-1">Model Accuracy</div>
          </div>
        </div>

        <p className="mt-12 text-xs text-gray-600 max-w-lg mx-auto">
          Data from Idaho Department of Fish and Game. Weather from Open-Meteo.
          Predictions are statistical estimates — not guarantees.
          Always check current regulations at idfg.idaho.gov.
        </p>
      </div>
    </div>
  );
}
