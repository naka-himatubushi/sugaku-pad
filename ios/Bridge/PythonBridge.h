//
//  埋め込み CPython への最小ブリッジ。
//  Swift から PythonBridge.solveJSON(latex) を呼ぶと、バンドルした mathai が
//  解いた結果を JSON 文字列で返す。初回呼び出しで Python を一度だけ初期化する。
//
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface PythonBridge : NSObject
/// Python ランタイムを初期化（多重呼び出しは無視）。成功で YES。
+ (BOOL)startup;
/// LaTeX/数式文字列を mathai に渡し、結果 dict を JSON 文字列で返す。
+ (NSString *)solveJSON:(NSString *)latex;
@end

NS_ASSUME_NONNULL_END
