// 端末内推論の RAM 使用量を実測するための計測ヘルパ。
// iOS が jetsam（メモリ不足での強制終了）判定に使う phys_footprint を読む。
// これが「このアプリが実際に消費している RAM」に最も近い指標。
import Foundation

enum MemoryProbe {
    /// 現在の物理フットプリント（MB）。iOS のメモリ上限判定と同じ指標。
    static func footprintMB() -> Double {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(
            MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<integer_t>.size)
        let kr = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count)
            }
        }
        guard kr == KERN_SUCCESS else { return 0 }
        return Double(info.phys_footprint) / 1024 / 1024
    }

    /// jetsam で殺されるまでに使える残り RAM（MB）。値が小さいほど危険。
    static func availableMB() -> Double {
        Double(os_proc_available_memory()) / 1024 / 1024
    }
}
